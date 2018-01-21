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

  render() {
    let content = 
    <TableRow>
      <TableHeaderColumn>Could not find available JOB</TableHeaderColumn>
    </TableRow>
    if(this.state.data !== null) {
      content = Object.keys(this.state.data).map((_row, i) => {
        console.log(this.state.data[_row]);
        return <TableRow>
          <TableHeaderColumn>{this.state.data[_row].auth}</TableHeaderColumn>
          <TableHeaderColumn>{this.state.data[_row].id.substr(0,8)}</TableHeaderColumn>
          <TableHeaderColumn>{this.state.data[_row].amount}</TableHeaderColumn>
          <TableHeaderColumn>{this.state.data[_row].status_list[0].block}</TableHeaderColumn>
        </TableRow>
      });
    }

    return (
      <Card style={{"margin":16}}>
        <CardHeader
          title="Available Jobs"
          subtitle="These jobs are not yet assigned"
        />
        <CardText>
          <Table selectable={false}>
            <TableHeader displaySelectAll={false} adjustForCheckbox={false}>
              <TableRow selectable={false}>
                <TableHeaderColumn>Sub Authority</TableHeaderColumn>
                <TableHeaderColumn>Job ID</TableHeaderColumn>
                <TableHeaderColumn>Reward</TableHeaderColumn>
                <TableHeaderColumn>Announced Block</TableHeaderColumn>
              </TableRow>
            </TableHeader>
            <TableBody displayRowCheckbox={false}>
              {content}
            </TableBody>
          </Table>
        </CardText>
      </Card>
    );
  }
}

export default JobListing;