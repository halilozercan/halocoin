import React, { Component } from 'react';
import axios from 'axios';
import {
  Table,
  TableBody,
  TableHeader,
  TableHeaderColumn,
  TableRow,
} from 'material-ui/Table';
import {Card, CardHeader, CardText} from 'material-ui/Card';

class JobListing extends Component {

  constructor(props) {
    super(props);
    this.state = {
      data: null,
      dialogOpen: false,
      jobId: '',
      offer: '0',
      rowsPerPage: [5,10,15],
      numberOfRows: 5,
      page: 1,
      total: 0
    }
  }

  componentDidMount() {
    this.updateRows();
  }

  updateRows = (state) => {
    axios.get('/available_jobs', {
      params: {
        page: this.state.page,
        row_per_page: this.state.numberOfRows
      }
    }).then((response) => {
      this.setState({
        data: response.data.jobs,
        total: response.data.total
      });
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