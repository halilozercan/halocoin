import React, { Component } from 'react';
import {axiosInstance} from '../tools.js';
import {
  Table,
  TableBody,
  TableHeader,
  TableHeaderColumn,
  TableRow,
  TableRowColumn,
} from 'material-ui/Table';
import {Card, CardActions, CardHeader, CardText} from 'material-ui/Card';
import RaisedButton from 'material-ui/RaisedButton';
import Dialog from 'material-ui/Dialog';
import TextField from 'material-ui/TextField';

class JobListing extends Component {

  constructor(props) {
    super(props);
    this.state = {
      data: null,
      dialogOpen: false,
      jobId: '',
      offer: '0'
    }
  }

  componentDidMount() {
    axiosInstance.get('/jobs').then((response) => {
      this.setState({data: response.data.available});
    });
  }

  handleOpen = (job_id) => {
    this.setState({dialogOpen: true, jobId: job_id});
  };

  handleClose = () => {
    this.setState({dialogOpen: false, jobId: ''});
  };

  onChange = (e) => {
    const state = this.state
    state[e.target.name] = e.target.value;
    this.setState(state);
  };

  bidNow = () => {
    let data = new FormData();
    data.append('job_id', this.state.jobId);
    data.append('amount', this.state.offer);
    data.append('password', this.state.password);

    axiosInstance.post('/job_request', data).then((response) => {
      let success = response.data.success;
      if(success) {
        this.props.notify('Your job request is added to the pool', 'success');
      }
      else {
        this.props.notify('Failed to add your job request', 'error');
      }
    })

    this.setState({dialogOpen: false});
  }

  render() {
    let content = 
    <TableRow>
      <TableHeaderColumn>Could not find available JOB</TableHeaderColumn>
    </TableRow>
    if(this.state.data !== null) {
      content = Object.keys(this.state.data).map((_row, i) => {
        console.log(this.state.data[_row]);
        return <TableRow>
          <TableHeaderColumn>{this.state.data[_row].id}</TableHeaderColumn>
          <TableHeaderColumn>10000</TableHeaderColumn>
          <TableHeaderColumn>{this.state.data[_row].status_list[0].block}</TableHeaderColumn>
          <TableHeaderColumn><RaisedButton label="Bid" primary={true} onClick={ () => {this.handleOpen(this.state.data[_row].id)} } /></TableHeaderColumn>
        </TableRow>
      });
    }

    const actions = [
      <RaisedButton
        label="Ok"
        primary={true}
        keyboardFocused={true}
        onClick={this.bidNow}
      />,
    ];

    return (
      <Card style={{"margin":16}}>
        <CardHeader
          title="Available Jobs"
          subtitle="Bid on these jobs to get assigned"
        />
        <CardText>
          <Table selectable={false}>
            <TableHeader displaySelectAll={false} adjustForCheckbox={false}>
              <TableRow selectable={false}>
                <TableHeaderColumn>Job ID</TableHeaderColumn>
                <TableHeaderColumn>Max Reward</TableHeaderColumn>
                <TableHeaderColumn>Announced Block</TableHeaderColumn>
                <TableHeaderColumn>Auction</TableHeaderColumn>
              </TableRow>
            </TableHeader>
            <TableBody displayRowCheckbox={false}>
              {content}
            </TableBody>
          </Table>
        </CardText>
        <Dialog
          title="Bidding"
          actions={actions}
          modal={false}
          open={this.state.dialogOpen}
          onRequestClose={this.handleClose}
        >
          <TextField
              fullWidth={true}
              floatingLabelText="Offer"
              name="offer"
              type="text"
              onChange={this.onChange}
            />

          <TextField
            fullWidth={true}
            floatingLabelText="Password"
            name="password"
            type="password"
            onChange={this.onChange}
          />
        </Dialog>
      </Card>
    );
  }
}

export default JobListing;